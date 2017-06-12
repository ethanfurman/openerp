openerp.pad = function(instance) {
    
    instance.web.form.FieldPad = instance.web.form.AbstractField.extend({
        template: 'FieldPad',
        configured: false,
        content: "",
        start: function() {
            this._super();
            var self  = this;
            this.on('change:effective_readonly',this,function(){
                self.renderElement();
            });
        },
        render_value: function() {
            var self = this;
            var _super = _.bind(this._super, this);
            if (this.get("value") === false || this.get("value") === "") {
                self.view.dataset.call('pad_generate_url',{context:{
                        model: self.view.model,
                        field_name: self.name,
                        object_id: self.view.datarecord.id
                    }}).done(function(data) {
                    if(data&&data.url){
                        self.set({value: data.url.substr(4)});
                        _super(data.url);
                        self.renderElement();
                    }
                });
            } else {
                var url = self.get("value");
                if (_.str.startsWith(url, 'http')){
                    url = url.substr(4);
                }
                self.internal_set_value(url);
                self.renderElement();
            }
            this._dirty_flag = true;
        },
        renderElement: function(){
            var self  = this;
            var value = this.get('value');
            if (this.pad_loading_request) {
                this.pad_loading_request.abort();
            }
            if (value === false || value === ""){
                this.configured = false;
                this.content = "";
            }else{
                if (!_.str.startsWith(value,'http')){
                    value = 'http' + value;
                }
                this.configured = true;
                if(!this.get('effective_readonly')){
                    this.content = '<iframe width="100%" height="100%" frameborder="0" src="'+value+'?showChat=false&userName='+this.session.username+'"></iframe>';
                }else{
                    this.content = '<div class="oe_pad_loading">... Loading pad ...</div>';
                    var xhr = new XMLHttpRequest();
                    xhr.onload = function() {
                        var data = this.responseText;
                        var groups = /\<\s*body\s*\>([\s\S]*?)\<\s*\/body\s*\>/.exec(data);
                        data = (groups || []).length >= 2 ? groups[1] : '<br/>';
                        var invite = /You can invite others to share this pad./.exec(data);
                        var advert = /Welcome to Etherpad!/.exec(data);
                        if (invite || advert || data === "<br/>") {
                            data = '<br/>';
                        } else {
                            groups = /([\s\S]*?)\<div style="display:none.*?\<\/div\>([\s\S]*?)/.exec(data);
                            data = (groups || []).length >= 2 ? groups[1] : groups[0];
                        }
                        self.$('.oe_pad_content').html('<div class="oe_pad_readonly"><div>');
                        self.$('.oe_pad_readonly').html(data);
                    };
                    xhr.onerror = function() {
                        self.$('.oe_pad_content').text('Unable to load pad');
                    };
                    this.pad_loading_request = xhr;
                    xhr.open('GET', value+'/export/html', true);
                    xhr.send();
                }
            }
            this._super();
            this.$('.oe_pad_content').html(this.content);
            this.$('.oe_pad_switch').click(function(){
                self.$el.toggleClass('oe_pad_fullscreen');
            });
        },
    });

    instance.web.form.widgets = instance.web.form.widgets.extend({
        'pad': 'instance.web.form.FieldPad',
    });
};
